from __future__ import annotations

from datetime import datetime

from app.alpha.contracts import AlphaEvent


def _sort_key(event: AlphaEvent) -> datetime:
    try:
        return datetime.fromisoformat(event.data)
    except ValueError:
        return datetime.min


def build_timeline(events: list[AlphaEvent]) -> list[AlphaEvent]:
    return sorted(events, key=_sort_key, reverse=True)
