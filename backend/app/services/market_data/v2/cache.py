from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MarketDataCacheEntry
from app.services.market_data.v2.contracts import NormalizedMarketData


@dataclass
class CacheRecord:
    data: NormalizedMarketData
    expires_at: datetime


class InMemoryMarketDataCache:
    def __init__(self) -> None:
        self._items: dict[str, CacheRecord] = {}

    def get(self, key: str) -> NormalizedMarketData | None:
        record = self._items.get(key)
        if record is None or _is_expired(record.expires_at):
            return None
        return record.data.with_warning("cache_hit")

    def get_any(self, key: str) -> NormalizedMarketData | None:
        record = self._items.get(key)
        return record.data.with_warning("stale_cache") if record else None

    def set(self, key: str, data: NormalizedMarketData, ttl_seconds: int) -> None:
        self._items[key] = CacheRecord(
            data=data,
            expires_at=_utcnow() + timedelta(seconds=ttl_seconds),
        )


class DatabaseMarketDataCache:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, key: str) -> NormalizedMarketData | None:
        row = self.db.execute(select(MarketDataCacheEntry).where(MarketDataCacheEntry.cache_key == key)).scalar_one_or_none()
        if row is None or _is_expired(row.expires_at):
            return None
        return NormalizedMarketData.from_dict(json.loads(row.payload_json)).with_warning("cache_hit")

    def get_any(self, key: str) -> NormalizedMarketData | None:
        row = self.db.execute(select(MarketDataCacheEntry).where(MarketDataCacheEntry.cache_key == key)).scalar_one_or_none()
        if row is None:
            return None
        return NormalizedMarketData.from_dict(json.loads(row.payload_json)).with_warning("stale_cache")

    def set(self, key: str, data: NormalizedMarketData, ttl_seconds: int) -> None:
        expires_at = _utcnow() + timedelta(seconds=ttl_seconds)
        row = self.db.execute(select(MarketDataCacheEntry).where(MarketDataCacheEntry.cache_key == key)).scalar_one_or_none()
        if row is None:
            row = MarketDataCacheEntry(cache_key=key)
            self.db.add(row)
        row.provider = data.provider
        row.data_type = data.data_type
        row.payload_json = json.dumps(data.to_dict(), ensure_ascii=True)
        row.quality_score = data.quality_score
        row.expires_at = expires_at
        row.updated_at = _utcnow()
        self.db.flush()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=None)
    return expires_at <= _utcnow()
