from __future__ import annotations

from html.parser import HTMLParser
import re
import threading
import time
import unicodedata
from urllib.parse import quote, urljoin
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import get_settings
from app.services.market_data.v2.contracts import (
    DATA_TYPE_FUNDAMENTALS,
    MarketDataProviderBlocked,
    MarketDataProviderError,
    MarketDataProviderRateLimited,
    MarketDataProviderTimeout,
    MarketDataRequest,
    NormalizedMarketData,
)
from app.services.market_data.v2.normalization import normalize_fundamentals


USER_AGENT = "CarteiraAlpha360/0.1 (+local-validation-provider)"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tokens: list[str] = []

    def handle_data(self, data: str) -> None:
        value = re.sub(r"\s+", " ", data).strip()
        if value:
            self.tokens.append(value)


def _label_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.lower()).strip()


def _parse_brazilian_number(value: str) -> float | None:
    cleaned = (
        value.replace("%", "")
        .replace("R$", "")
        .replace("\xa0", " ")
        .replace(" ", "")
        .strip()
    )
    if not cleaned or cleaned in {"-", "--", "n/a", "N/A"}:
        return None
    negative = cleaned.startswith("-")
    cleaned = cleaned.lstrip("-")
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        cleaned = cleaned.replace(".", "")
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return -number if negative else number


LABEL_MAP = {
    "p l": "pe_ratio",
    "p vp": "pvp",
    "ev ebitda": "ev_ebitda",
    "roe": "roe",
    "roic": "roic",
    "marg liquida": "net_margin",
    "margem liquida": "net_margin",
    "div liquida ebitda": "debt_to_ebitda",
    "divida liquida ebitda": "debt_to_ebitda",
    "div yield": "dividend_yield",
    "dividend yield": "dividend_yield",
    "payout": "payout",
    "receita liquida": "revenue",
    "receita": "revenue",
    "lucro liquido": "profit",
    "lucro": "profit",
    "valor de mercado": "market_value",
}


def extract_fundamentus_indicators(html: str) -> dict[str, float]:
    parser = _TextExtractor()
    parser.feed(html)
    payload: dict[str, float] = {}
    for index, token in enumerate(parser.tokens[:-1]):
        metric_key = LABEL_MAP.get(_label_key(token))
        if metric_key is None or metric_key in payload:
            continue
        parsed = _parse_brazilian_number(parser.tokens[index + 1])
        if parsed is not None:
            payload[metric_key] = parsed
    return payload


class FundamentusProviderV2:
    """Optional secondary provider used only for fundamental validation."""

    name = "fundamentus"
    priority = 60
    _lock = threading.Lock()
    _last_request_at = 0.0

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.fundamentus_base_url.rstrip("/")
        self.timeout = self.settings.fundamentus_timeout_seconds

    def supports(self, data_type: str, request: MarketDataRequest) -> bool:
        if not self.settings.fundamentus_enabled:
            return False
        if data_type != DATA_TYPE_FUNDAMENTALS:
            return False
        if (request.asset_class or "").lower() in {"cripto", "crypto"}:
            return False
        market = (request.market or "B3").upper()
        return market in {"B3", "BR", "BRASIL", ""}

    def fetch(self, data_type: str, request: MarketDataRequest) -> NormalizedMarketData:
        self._enforce_rate_limit()
        warnings = self._robots_warnings("/detalhes.php")
        symbol = quote(request.normalized_symbol)
        url = urljoin(f"{self.base_url}/", f"detalhes.php?papel={symbol}")
        try:
            with httpx.Client(timeout=self.timeout, headers={"User-Agent": USER_AGENT}) as client:
                response = client.get(url)
        except httpx.TimeoutException as exc:
            raise MarketDataProviderTimeout("Fundamentus timeout") from exc
        except httpx.HTTPError as exc:
            raise MarketDataProviderError(f"Fundamentus indisponivel: {exc}") from exc

        if response.status_code == 403:
            raise MarketDataProviderBlocked("Fundamentus bloqueou a requisicao", status_code=403)
        if response.status_code >= 400:
            raise MarketDataProviderError(
                f"Fundamentus retornou status {response.status_code}",
                status_code=response.status_code,
            )

        indicators = extract_fundamentus_indicators(response.text)
        if not indicators:
            warnings = (*warnings, "empty_fundamentus_payload")

        return normalize_fundamentals(
            self.name,
            request,
            raw=indicators,
            currency=request.currency or "BRL",
        ).with_warning("secondary_validation_source").with_warning("|".join(warnings) if warnings else "robots_checked")

    def _enforce_rate_limit(self) -> None:
        now = time.monotonic()
        with self._lock:
            wait_seconds = max(0.0, self.settings.fundamentus_rate_limit_seconds - (now - self._last_request_at))
            if wait_seconds > 0:
                if wait_seconds <= 5:
                    time.sleep(wait_seconds)
                else:
                    raise MarketDataProviderRateLimited(
                        f"Fundamentus rate limit ativo por mais {wait_seconds:.1f}s"
                    )
            self._last_request_at = now

    def _robots_warnings(self, path: str) -> tuple[str, ...]:
        robots_url = f"{self.base_url}/robots.txt"
        try:
            response = httpx.get(robots_url, timeout=self.timeout, headers={"User-Agent": USER_AGENT})
        except httpx.TimeoutException as exc:
            raise MarketDataProviderTimeout("Timeout ao verificar robots.txt do Fundamentus") from exc
        except httpx.HTTPError as exc:
            raise MarketDataProviderBlocked("Nao foi possivel verificar robots.txt do Fundamentus") from exc

        if response.status_code == 404:
            return ("robots_not_found_404",)
        if response.status_code == 403:
            raise MarketDataProviderBlocked("Fundamentus bloqueou verificacao de robots.txt", status_code=403)
        if response.status_code >= 400:
            raise MarketDataProviderBlocked(
                f"Fundamentus robots.txt retornou status {response.status_code}",
                status_code=response.status_code,
            )

        robot_parser = RobotFileParser(robots_url)
        robot_parser.parse(response.text.splitlines())
        target_url = urljoin(f"{self.base_url}/", path.lstrip("/"))
        if not robot_parser.can_fetch(USER_AGENT, target_url):
            raise MarketDataProviderBlocked("robots.txt nao permite coleta deste caminho")
        return ("robots_allowed",)
