from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from typing import Any, Protocol


DATA_TYPE_QUOTE = "quote"
DATA_TYPE_FUNDAMENTALS = "fundamentals"
DATA_TYPE_DIVIDENDS = "dividends"
DATA_TYPE_PRICE_HISTORY = "price_history"
DATA_TYPE_FX_RATE = "fx_rate"
DATA_TYPE_ASSET_SEARCH = "asset_search"


@dataclass(frozen=True)
class MarketDataRequest:
    symbol: str = ""
    asset_id: str | None = None
    provider_symbol: str = ""
    market: str = ""
    asset_class: str = ""
    currency: str = "BRL"
    base_currency: str = ""
    quote_currency: str = ""
    start_date: date | None = None
    end_date: date | None = None
    interval: str = "1d"
    query: str = ""

    @property
    def normalized_symbol(self) -> str:
        return (self.provider_symbol or self.symbol or self.query).strip().upper()


@dataclass(frozen=True)
class NormalizedMarketData:
    data_type: str
    provider: str
    source_symbol: str
    payload: dict[str, Any]
    asset_id: str | None = None
    currency: str = "BRL"
    as_of: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    quality_score: float = 0
    warnings: tuple[str, ...] = ()

    def with_warning(self, warning: str) -> "NormalizedMarketData":
        return replace(self, warnings=(*self.warnings, warning))

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "data_type": self.data_type,
            "provider": self.provider,
            "source_symbol": self.source_symbol,
            "currency": self.currency,
            "as_of": self.as_of.isoformat(),
            "payload": self.payload,
            "quality_score": self.quality_score,
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NormalizedMarketData":
        raw_as_of = data.get("as_of")
        if isinstance(raw_as_of, str):
            as_of = datetime.fromisoformat(raw_as_of)
        elif isinstance(raw_as_of, datetime):
            as_of = raw_as_of
        else:
            as_of = datetime.now(timezone.utc)
        return cls(
            asset_id=data.get("asset_id"),
            data_type=data["data_type"],
            provider=data["provider"],
            source_symbol=data.get("source_symbol", ""),
            currency=data.get("currency", "BRL"),
            as_of=as_of,
            payload=data.get("payload", {}),
            quality_score=float(data.get("quality_score") or 0),
            warnings=tuple(data.get("warnings") or ()),
        )


class MarketDataProviderV2(Protocol):
    name: str
    priority: int

    def supports(self, data_type: str, request: MarketDataRequest) -> bool:
        ...

    def fetch(self, data_type: str, request: MarketDataRequest) -> NormalizedMarketData:
        ...


class MarketDataUnavailable(RuntimeError):
    pass


class MarketDataProviderError(RuntimeError):
    """Base class for provider failures that should be captured and fall back."""

    def __init__(self, message: str, *, status_code: int | str | None = None) -> None:
        super().__init__(message)
        self.status_code = "" if status_code is None else str(status_code)


class MarketDataProviderBlocked(MarketDataProviderError):
    pass


class MarketDataProviderTimeout(MarketDataProviderError):
    pass


class MarketDataProviderRateLimited(MarketDataProviderError):
    pass
