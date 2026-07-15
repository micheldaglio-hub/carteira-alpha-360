from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import UserPreference
from app.schemas import DashboardProjectionPremises, ProjectionRequest


PROJECTION_PREMISES_KEY = "projection_premises"
DASHBOARD_PROJECTION_PREMISES_KEY = "dashboard_projection_premises"


def get_projection_premises(db: Session, user_id: str) -> dict[str, Any] | None:
    preference = _get_preference(db, user_id, PROJECTION_PREMISES_KEY)
    if preference is None or not preference.value_json:
        return None
    try:
        data = json.loads(preference.value_json)
        return ProjectionRequest(**data).model_dump()
    except (TypeError, ValueError):
        return None


def save_projection_premises(db: Session, user_id: str, payload: ProjectionRequest) -> dict[str, Any]:
    preference = _get_preference(db, user_id, PROJECTION_PREMISES_KEY)
    if preference is None:
        preference = UserPreference(user_id=user_id, key=PROJECTION_PREMISES_KEY)
        db.add(preference)
    preference.value_json = json.dumps(payload.model_dump(), ensure_ascii=False, sort_keys=True)
    preference.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(preference)
    return payload.model_dump()


def delete_projection_premises(db: Session, user_id: str) -> None:
    preference = _get_preference(db, user_id, PROJECTION_PREMISES_KEY)
    if preference is not None:
        db.delete(preference)
        db.commit()


def get_dashboard_projection_premises(db: Session, user_id: str) -> dict[str, Any] | None:
    preference = _get_preference(db, user_id, DASHBOARD_PROJECTION_PREMISES_KEY)
    if preference is None or not preference.value_json:
        return None
    try:
        data = json.loads(preference.value_json)
        return DashboardProjectionPremises(**data).model_dump()
    except (TypeError, ValueError):
        return None


def save_dashboard_projection_premises(db: Session, user_id: str, payload: DashboardProjectionPremises) -> dict[str, Any]:
    preference = _get_preference(db, user_id, DASHBOARD_PROJECTION_PREMISES_KEY)
    if preference is None:
        preference = UserPreference(user_id=user_id, key=DASHBOARD_PROJECTION_PREMISES_KEY)
        db.add(preference)
    preference.value_json = json.dumps(payload.model_dump(), ensure_ascii=False, sort_keys=True)
    preference.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(preference)
    return payload.model_dump()


def delete_dashboard_projection_premises(db: Session, user_id: str) -> None:
    preference = _get_preference(db, user_id, DASHBOARD_PROJECTION_PREMISES_KEY)
    if preference is not None:
        db.delete(preference)
        db.commit()


def _get_preference(db: Session, user_id: str, key: str) -> UserPreference | None:
    return (
        db.execute(
            select(UserPreference).where(
                UserPreference.user_id == user_id,
                UserPreference.key == key,
            )
        )
        .scalars()
        .first()
    )
