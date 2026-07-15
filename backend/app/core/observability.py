from __future__ import annotations

import json
import logging
import sys
from collections import Counter, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any


LOGGER_NAME = "carteira_alpha"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status_code", "duration_ms", "user_id", "event_type", "job_name"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(json_logs: bool = True) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if json_logs else logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


@dataclass
class RequestMetric:
    request_id: str
    method: str
    path: str
    status_code: int
    duration_ms: float
    timestamp: str


class ObservabilityState:
    def __init__(self) -> None:
        self.started_at = datetime.now(UTC)
        self._lock = Lock()
        self._requests: deque[RequestMetric] = deque(maxlen=250)
        self._status_counter: Counter[str] = Counter()
        self._path_counter: Counter[str] = Counter()
        self._errors: deque[dict[str, Any]] = deque(maxlen=100)

    def record_request(self, *, request_id: str, method: str, path: str, status_code: int, duration_ms: float) -> None:
        metric = RequestMetric(
            request_id=request_id,
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            timestamp=datetime.now(UTC).isoformat(),
        )
        with self._lock:
            self._requests.append(metric)
            self._status_counter[str(status_code)] += 1
            self._path_counter[f"{method} {path}"] += 1
            if status_code >= 500:
                self._errors.append(
                    {
                        "requestId": request_id,
                        "method": method,
                        "path": path,
                        "statusCode": status_code,
                        "durationMs": duration_ms,
                        "timestamp": metric.timestamp,
                    }
                )

    def record_error(self, *, request_id: str, method: str, path: str, message: str) -> None:
        with self._lock:
            self._errors.append(
                {
                    "requestId": request_id,
                    "method": method,
                    "path": path,
                    "message": message,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            requests = list(self._requests)
            total = len(requests)
            durations = [item.duration_ms for item in requests]
            return {
                "status": "operational",
                "startedAt": self.started_at.isoformat(),
                "uptimeSeconds": round((datetime.now(UTC) - self.started_at).total_seconds(), 2),
                "requestsWindow": total,
                "avgDurationMs": round(sum(durations) / total, 2) if total else 0,
                "maxDurationMs": round(max(durations), 2) if durations else 0,
                "statusCodes": dict(self._status_counter),
                "topPaths": [{"path": key, "count": value} for key, value in self._path_counter.most_common(10)],
                "recentErrors": list(self._errors)[-10:],
                "recentRequests": [item.__dict__ for item in requests[-20:]],
            }


observability_state = ObservabilityState()
logger = logging.getLogger(LOGGER_NAME)
