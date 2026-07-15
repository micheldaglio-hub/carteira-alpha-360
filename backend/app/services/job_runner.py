from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.observability import logger
from app.database import SessionLocal
from app.models import JobRun, MarketDataCacheEntry, User
from app.services.audit import purge_old_audit_events, write_audit_event
from app.services.financial_formula_auditor import run_financial_formula_audit
from app.services.market_data.sync import sync_user_assets
from app.services.model_portfolios import get_model_portfolios
from app.wealth_os.guardian_engine import build_guardian_report
from app.wealth_os.macro_fx_engine import EconomicMacroFxEngine


JobFunction = Callable[[Session], dict[str, Any]]


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, JobFunction] = {
            "ops.heartbeat": run_heartbeat,
            "ops.cleanup": run_cleanup,
            "guardian.snapshot": run_guardian_snapshot,
            "market_data.user_assets": run_market_data_sync,
            "market_data.model_portfolios": run_model_portfolios_sync,
            "macro_fx.refresh": run_macro_fx_refresh,
            "financial.formula_audit": run_formula_audit,
        }

    def names(self) -> list[str]:
        return sorted(self._jobs)

    def get(self, name: str) -> JobFunction:
        if name not in self._jobs:
            raise KeyError(name)
        return self._jobs[name]


class BackgroundJobScheduler:
    def __init__(self) -> None:
        self._tasks: list[asyncio.Task] = []
        self._started = False

    def start(self) -> None:
        settings = get_settings()
        if self._started or not settings.jobs_enabled:
            return
        self._started = True
        loop = asyncio.get_running_loop()
        self._tasks = [
            loop.create_task(self._run_periodic("ops.heartbeat", settings.jobs_heartbeat_interval_seconds)),
            loop.create_task(self._run_periodic("ops.cleanup", settings.jobs_cleanup_interval_seconds)),
            loop.create_task(self._run_periodic("guardian.snapshot", settings.jobs_guardian_interval_seconds)),
            loop.create_task(self._run_periodic("market_data.user_assets", settings.jobs_market_data_interval_seconds)),
            loop.create_task(self._run_periodic("market_data.model_portfolios", settings.jobs_model_portfolios_interval_seconds)),
            loop.create_task(self._run_periodic("macro_fx.refresh", settings.jobs_macro_fx_interval_seconds)),
            loop.create_task(self._run_periodic("financial.formula_audit", settings.jobs_formula_audit_interval_seconds)),
        ]
        logger.info("Background jobs started", extra={"job_name": "scheduler"})

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        self._started = False

    async def _run_periodic(self, job_name: str, interval_seconds: int) -> None:
        interval = max(30, int(interval_seconds or 300))
        while True:
            await asyncio.sleep(interval)
            await asyncio.to_thread(run_job_by_name, job_name)


scheduler = BackgroundJobScheduler()


def run_job_by_name(job_name: str) -> dict[str, Any]:
    job = registry.get(job_name)
    db = SessionLocal()
    try:
        return execute_job(db, job_name, job)
    finally:
        db.close()


def execute_job(db: Session, job_name: str, job: JobFunction) -> dict[str, Any]:
    started = perf_counter()
    run = JobRun(job_name=job_name, status="running", details_json="{}")
    db.add(run)
    db.commit()
    db.refresh(run)
    try:
        result = job(db)
        duration_ms = int((perf_counter() - started) * 1000)
        run.status = "success"
        run.finished_at = datetime.now(UTC)
        run.duration_ms = duration_ms
        run.rows_affected = int(result.get("rowsAffected") or 0)
        run.message = str(result.get("message") or "Job executado com sucesso.")
        run.details_json = json.dumps(result, ensure_ascii=False, default=str)
        db.commit()
        logger.info(run.message, extra={"job_name": job_name})
        return job_run_to_dict(run)
    except Exception as exc:
        duration_ms = int((perf_counter() - started) * 1000)
        run.status = "error"
        run.finished_at = datetime.now(UTC)
        run.duration_ms = duration_ms
        run.message = str(exc)[:500]
        run.details_json = json.dumps({"error": str(exc)}, ensure_ascii=False)
        db.commit()
        logger.exception("Job failed", extra={"job_name": job_name})
        return job_run_to_dict(run)


def run_heartbeat(db: Session) -> dict[str, Any]:
    write_audit_event(
        db,
        event_type="ops_heartbeat",
        category="observability",
        action="heartbeat",
        actor_type="system",
        severity="info",
        message="Heartbeat operacional registrado.",
        metadata={"source": "background_job"},
    )
    return {"message": "Heartbeat operacional registrado.", "rowsAffected": 1}


def run_cleanup(db: Session) -> dict[str, Any]:
    settings = get_settings()
    audit_deleted = purge_old_audit_events(db, retention_days=settings.audit_retention_days)
    cache_result = db.execute(delete(MarketDataCacheEntry).where(MarketDataCacheEntry.expires_at < datetime.now(UTC)))
    db.commit()
    cache_deleted = int(cache_result.rowcount or 0)
    return {
        "message": "Limpeza operacional concluida.",
        "rowsAffected": audit_deleted + cache_deleted,
        "auditDeleted": audit_deleted,
        "expiredCacheDeleted": cache_deleted,
    }


def run_guardian_snapshot(db: Session) -> dict[str, Any]:
    users = list(db.execute(select(User)).scalars().all())
    reports = []
    for user in users:
        report = build_guardian_report(db, user.id)
        reports.append({"userId": user.id, "status": report.status, "items": report.summary.get("total", 0)})
    write_audit_event(
        db,
        event_type="guardian_snapshot",
        category="guardian",
        action="snapshot",
        actor_type="system",
        severity="info",
        message=f"Guardian snapshot executado para {len(users)} usuario(s).",
        metadata={"reports": reports},
    )
    return {"message": "Guardian snapshot executado.", "rowsAffected": len(users), "reports": reports}


def run_market_data_sync(db: Session) -> dict[str, Any]:
    users = list(db.execute(select(User)).scalars().all())
    reports = []
    rows_affected = 0
    for user in users:
        result = sync_user_assets(db, user.id)
        updated = result.get("updated", [])
        skipped = result.get("skipped", [])
        rows_affected += len(updated)
        reports.append({"userId": user.id, "updated": updated, "skipped": skipped})
    write_audit_event(
        db,
        event_type="market_data_user_assets_sync",
        category="market_data",
        action="sync_user_assets",
        actor_type="system",
        severity="info",
        message=f"Market Data Engine sincronizou ativos de {len(users)} usuario(s).",
        metadata={"reports": reports},
    )
    return {
        "message": "Market Data Engine sincronizou ativos das carteiras.",
        "rowsAffected": rows_affected,
        "reports": reports,
    }


def run_model_portfolios_sync(db: Session) -> dict[str, Any]:
    users = list(db.execute(select(User)).scalars().all())
    reports = []
    for user in users:
        result = get_model_portfolios(db, user_id=user.id, refresh_market=True)
        reports.append(
            {
                "userId": user.id,
                "institutionalScore": result.get("recommendedPortfolioReport", {}).get("institutionalScore"),
                "confidenceScore": result.get("confidenceReport", {}).get("overallScore"),
                "governanceReviewId": result.get("recommendationGovernance", {}).get("reviewId"),
                "governanceDecision": result.get("recommendationGovernance", {}).get("decision"),
            }
        )
    write_audit_event(
        db,
        event_type="model_portfolio_monthly_review",
        category="recommendation_governance",
        action="refresh_model_portfolios",
        actor_type="system",
        severity="info",
        message=f"Carteiras recomendadas revisadas para {len(users)} usuario(s).",
        metadata={"reports": reports},
    )
    return {
        "message": "Carteiras recomendadas e governanca recalculadas.",
        "rowsAffected": len(users),
        "reports": reports,
    }


def run_macro_fx_refresh(db: Session) -> dict[str, Any]:
    users = list(db.execute(select(User)).scalars().all())
    engine = EconomicMacroFxEngine()
    reports = []
    warnings = []
    for user in users:
        snapshot = engine.build_snapshot(db, user.id, refresh=True)
        reports.append(
            {
                "userId": user.id,
                "status": snapshot.status,
                "updatedAt": snapshot.updatedAt,
                "warnings": snapshot.warnings,
            }
        )
        warnings.extend(snapshot.warnings)
    write_audit_event(
        db,
        event_type="macro_fx_refresh",
        category="macro_fx",
        action="refresh_macro_fx",
        actor_type="system",
        severity="warning" if warnings else "info",
        message=f"Macro/FX Engine atualizado para {len(users)} usuario(s).",
        metadata={"reports": reports, "warnings": sorted(set(warnings))},
    )
    return {
        "message": "Macro/FX Engine atualizado.",
        "rowsAffected": len(users),
        "reports": reports,
        "warnings": sorted(set(warnings)),
    }


def run_formula_audit(db: Session) -> dict[str, Any]:
    report = run_financial_formula_audit(db)
    if report["status"] != "pass":
        raise RuntimeError(f"Auditoria financeira falhou com score {report['score']}/100.")
    return {
        "message": "Auditoria real das formulas financeiras aprovada.",
        "rowsAffected": report["passed"],
        "report": report,
    }


registry = JobRegistry()


def list_job_runs(db: Session, *, limit: int = 50) -> list[dict]:
    rows = db.execute(select(JobRun).order_by(JobRun.started_at.desc()).limit(limit)).scalars().all()
    return [job_run_to_dict(item) for item in rows]


def job_status(db: Session) -> dict:
    latest = {}
    for name in registry.names():
        row = db.execute(select(JobRun).where(JobRun.job_name == name).order_by(JobRun.started_at.desc()).limit(1)).scalar_one_or_none()
        latest[name] = job_run_to_dict(row) if row else None
    return {"jobsEnabled": get_settings().jobs_enabled, "registeredJobs": registry.names(), "latestRuns": latest}


def job_run_to_dict(run: JobRun | None) -> dict | None:
    if run is None:
        return None
    try:
        details = json.loads(run.details_json or "{}")
    except json.JSONDecodeError:
        details = {}
    return {
        "id": run.id,
        "jobName": run.job_name,
        "status": run.status,
        "startedAt": run.started_at.isoformat() if run.started_at else "",
        "finishedAt": run.finished_at.isoformat() if run.finished_at else "",
        "durationMs": run.duration_ms,
        "rowsAffected": run.rows_affected,
        "message": run.message,
        "details": details,
    }
