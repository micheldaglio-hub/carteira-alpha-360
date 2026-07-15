from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.engine import Engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app import models  # noqa: F401,E402
from app.database import Base  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migra dados locais do Carteira Alpha 360 de SQLite para PostgreSQL/Supabase."
    )
    parser.add_argument(
        "--sqlite-url",
        default=f"sqlite:///{(BACKEND_ROOT / 'carteira_alpha.db').as_posix()}",
        help="URL do SQLite de origem. Padrao: backend/carteira_alpha.db.",
    )
    parser.add_argument("--postgres-url", required=True, help="URL PostgreSQL/Supabase de destino.")
    parser.add_argument("--apply", action="store_true", help="Grava os dados no PostgreSQL. Sem isso roda dry-run.")
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Apaga as tabelas do destino antes de copiar. Use somente com backup confirmado.",
    )
    args = parser.parse_args()

    source_url = _normalize_sqlite_url(args.sqlite_url)
    target_url = _normalize_postgres_url(args.postgres_url)
    _guard_urls(source_url, target_url)

    source = create_engine(source_url)
    target = create_engine(target_url, pool_pre_ping=True)

    tables = list(Base.metadata.sorted_tables)
    report: dict[str, Any] = {
        "mode": "apply" if args.apply else "dry-run",
        "source": _redact_url(source_url),
        "target": _redact_url(target_url),
        "truncate": bool(args.truncate),
        "tables": [],
    }

    if args.apply and args.truncate:
        _truncate_target(target, tables)

    for table in tables:
        rows = _fetch_rows(source, table)
        item = {"table": table.name, "rows": len(rows), "status": "planned"}
        if args.apply and rows:
            with target.begin() as connection:
                connection.execute(table.insert(), rows)
            item["status"] = "copied"
        elif args.apply:
            item["status"] = "empty"
        report["tables"].append(item)

    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    return 0


def _normalize_sqlite_url(url: str) -> str:
    value = url.strip()
    if value == "sqlite:///./backend/carteira_alpha.db":
        return f"sqlite:///{(PROJECT_ROOT / 'backend' / 'carteira_alpha.db').as_posix()}"
    if value == "sqlite:///./carteira_alpha.db":
        return f"sqlite:///{(BACKEND_ROOT / 'carteira_alpha.db').as_posix()}"
    return value


def _normalize_postgres_url(url: str) -> str:
    value = url.strip()
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value.removeprefix("postgresql://")
    return value


def _guard_urls(source_url: str, target_url: str) -> None:
    if not source_url.startswith("sqlite"):
        raise SystemExit("A origem precisa ser SQLite.")
    if not target_url.startswith("postgresql"):
        raise SystemExit("O destino precisa ser PostgreSQL/Supabase.")
    lowered = target_url.lower()
    if "[your-password]" in lowered or "sua_senha" in lowered or "senha" in lowered:
        raise SystemExit("Substitua a senha placeholder da connection string antes de migrar.")


def _fetch_rows(engine: Engine, table) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        if not engine.dialect.has_table(connection, table.name):
            return []
        return [dict(row._mapping) for row in connection.execute(select(table)).all()]


def _truncate_target(engine: Engine, tables) -> None:
    with engine.begin() as connection:
        for table in reversed(tables):
            if engine.dialect.has_table(connection, table.name):
                connection.execute(delete(table))


def _redact_url(url: str) -> str:
    if "@" not in url:
        return url
    prefix, suffix = url.rsplit("@", 1)
    if ":" not in prefix:
        return "***@" + suffix
    scheme_user, _password = prefix.rsplit(":", 1)
    return f"{scheme_user}:***@{suffix}"


if __name__ == "__main__":
    raise SystemExit(main())
