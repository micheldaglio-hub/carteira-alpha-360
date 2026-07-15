from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import get_settings
from app.core.observability import configure_logging, logger, observability_state
from app.core.runtime_safety import assert_runtime_safe, is_production, runtime_safety_findings
from app.database import Base, SessionLocal, engine
from app.routers import billing, distribution, alerts, auth, crypto, dashboard, integrations, intelligence, model_portfolios, ops, portfolio, premium, projections, radar, rebalance, settings, wealth_os
from app.seed import seed_demo_data
from app.services.audit import write_audit_event_best_effort
from app.services.job_runner import scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Compatibilidade local: Alembic passa a ser a fonte oficial de evolucao do schema.
    app_settings = get_settings()
    configure_logging(app_settings.observability_json_logs)
    assert_runtime_safe(app_settings)
    if app_settings.database_auto_create_tables:
        Base.metadata.create_all(bind=engine)
    if app_settings.seed_demo_data:
        db = SessionLocal()
        try:
            seed_demo_data(db)
        finally:
            db.close()
    scheduler.start()
    try:
        yield
    finally:
        await scheduler.stop()


app_settings = get_settings()
app = FastAPI(title=app_settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins,
    allow_origin_regex=app_settings.backend_cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(distribution.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(integrations.router, prefix="/api")
app.include_router(intelligence.router, prefix="/api")
app.include_router(crypto.router, prefix="/api")
app.include_router(model_portfolios.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(radar.router, prefix="/api")
app.include_router(projections.router, prefix="/api")
app.include_router(rebalance.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(wealth_os.router, prefix="/api")
app.include_router(ops.router, prefix="/api")
app.include_router(premium.router, prefix="/api")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
        observability_state.record_error(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            message=str(exc),
        )
        logger.exception(
            "request_failed",
            extra={"request_id": request_id, "method": request.method, "path": request.url.path, "duration_ms": elapsed_ms},
        )
        raise
    elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
    observability_state.record_request(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=elapsed_ms,
    )
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": elapsed_ms,
        },
    )
    if app_settings.audit_http_mutations and request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path.startswith("/api"):
        write_audit_event_best_effort(
            event_type="http_mutation",
            category="http",
            action=f"{request.method} {request.url.path}",
            actor_type="system",
            severity="warning" if response.status_code >= 400 else "info",
            resource_type="http_request",
            resource_id=request.url.path,
            request_id=request_id,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent", ""),
            message=f"{request.method} {request.url.path} retornou {response.status_code}.",
            metadata={"statusCode": response.status_code, "durationMs": elapsed_ms},
        )
    response.headers.setdefault("X-Request-ID", request_id)
    response.headers.setdefault("X-Process-Time-Ms", str(elapsed_ms))
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if is_production(app_settings) and request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")
    return response


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.get("/api/health")
def health():
    return {"status": "ok", "app": app_settings.app_name}


@app.get("/api/ready")
def readiness():
    db_ok = False
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    findings = runtime_safety_findings(app_settings)
    critical = [finding for finding in findings if finding.severity == "critical"]
    return {
        "status": "ready" if db_ok and not (is_production(app_settings) and critical) else "not_ready",
        "database": "ok" if db_ok else "error",
        "environment": app_settings.environment,
        "productionMode": is_production(app_settings),
        "criticalFindings": len(critical),
        "warnings": sum(1 for finding in findings if finding.severity == "warning"),
        "findings": [finding.as_dict() for finding in findings],
    }
