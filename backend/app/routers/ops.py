from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.observability import observability_state
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services.audit import audit_event_to_dict, audit_summary, list_audit_events, write_audit_event
from app.services.data_lineage import data_lineage_summary, evidence_to_dict, list_data_evidence
from app.services.job_runner import job_status, list_job_runs, registry, run_job_by_name


router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/observability")
def observability(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {
        "observability": observability_state.snapshot(),
        "audit": audit_summary(db, user_id=user.id),
        "dataLineage": data_lineage_summary(db, user_id=user.id),
        "jobs": job_status(db),
    }


@router.get("/audit")
def audit_events(
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    events = list_audit_events(db, user_id=user.id, limit=limit)
    return {"summary": audit_summary(db, user_id=user.id), "events": [audit_event_to_dict(item) for item in events]}


@router.get("/evidence")
def data_evidence(
    domain: str | None = Query(default=None),
    field_name: str | None = Query(default=None),
    asset_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = list_data_evidence(
        db,
        user_id=user.id,
        domain=domain,
        field_name=field_name,
        asset_id=asset_id,
        limit=limit,
    )
    return {
        "summary": data_lineage_summary(db, user_id=user.id),
        "evidence": [evidence_to_dict(item) for item in rows],
    }


@router.get("/jobs")
def jobs(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"status": job_status(db), "runs": list_job_runs(db, limit=limit)}


@router.post("/jobs/{job_name}/run")
def run_job(job_name: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if job_name not in registry.names():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job nao encontrado.")
    write_audit_event(
        db,
        event_type="manual_job_run_requested",
        category="jobs",
        action="run_job",
        user_id=user.id,
        severity="info",
        resource_type="job",
        resource_id=job_name,
        message=f"Usuario solicitou execucao manual do job {job_name}.",
    )
    result = run_job_by_name(job_name)
    return {"run": result}
