"""asset engine universal additive schema

Revision ID: 20260709_0002
Revises: 20260709_0001
Create Date: 2026-07-09 00:00:00
"""
from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa


revision = "20260709_0002"
down_revision = "20260709_0001"
branch_labels = None
depends_on = None


def _clean(value: object, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _upper(value: object, fallback: str = "") -> str:
    return _clean(value, fallback).upper()


def _code(value: object) -> str:
    return _upper(value).replace(" ", "_").replace("-", "_")


def _infer_metadata(row: dict) -> dict[str, str]:
    ticker = _upper(row.get("ticker"))
    asset_class = _clean(row.get("asset_class"))
    asset_class_lower = asset_class.lower()
    sector = _clean(row.get("sector"))
    segment = _clean(row.get("segment"))
    currency = _upper(row.get("currency"), "BRL") or "BRL"
    industry = segment or sector

    if asset_class_lower in {"cripto", "crypto"}:
        return {
            "universal_symbol": f"CRYPTO:{ticker}",
            "asset_subclass": segment or "Cryptoasset",
            "country_code": "",
            "region": "Global",
            "market": "Crypto",
            "exchange": "",
            "base_currency": ticker,
            "trading_currency": currency,
            "industry": industry or "Crypto",
            "status": "active",
        }

    if "fii" in asset_class_lower:
        asset_subclass = "Brazilian Real Estate Fund"
    elif "etf" in asset_class_lower:
        asset_subclass = "Brazilian Listed ETF"
    elif asset_class_lower in {"acoes", "ações", "acao", "ação", "equity", "stock"}:
        asset_subclass = "Brazilian Equity"
    else:
        asset_subclass = asset_class or "Unclassified Asset"

    return {
        "universal_symbol": f"BR:B3:{ticker}",
        "asset_subclass": asset_subclass,
        "country_code": "BR",
        "region": "Latin America",
        "market": "B3",
        "exchange": "B3",
        "base_currency": currency,
        "trading_currency": currency,
        "industry": industry,
        "status": "active",
    }


def _insert_identifier(connection, *, asset_id: str, identifier_type: str, identifier_value: str, provider: str, market: str, is_primary: bool) -> None:
    if not identifier_value:
        return
    connection.execute(
        sa.text(
            """
            insert into asset_identifiers
                (id, asset_id, identifier_type, identifier_value, provider, market, is_primary)
            values
                (:id, :asset_id, :identifier_type, :identifier_value, :provider, :market, :is_primary)
            """
        ),
        {
            "id": uuid.uuid4().hex,
            "asset_id": asset_id,
            "identifier_type": identifier_type,
            "identifier_value": identifier_value,
            "provider": provider,
            "market": market,
            "is_primary": is_primary,
        },
    )


def _insert_classification(connection, *, asset_id: str, taxonomy: str, level: str, code: str, label: str, source: str) -> None:
    if not code or not label:
        return
    connection.execute(
        sa.text(
            """
            insert into asset_classifications
                (id, asset_id, taxonomy, level, code, label, weight, source)
            values
                (:id, :asset_id, :taxonomy, :level, :code, :label, :weight, :source)
            """
        ),
        {
            "id": uuid.uuid4().hex,
            "asset_id": asset_id,
            "taxonomy": taxonomy,
            "level": level,
            "code": code,
            "label": label,
            "weight": 100,
            "source": source,
        },
    )


def _insert_exposure(connection, *, asset_id: str, exposure_type: str, exposure_key: str, percentage: int, source: str) -> None:
    if not exposure_key:
        return
    connection.execute(
        sa.text(
            """
            insert into asset_exposures
                (id, asset_id, exposure_type, exposure_key, percentage, source, as_of_date)
            values
                (:id, :asset_id, :exposure_type, :exposure_key, :percentage, :source, null)
            """
        ),
        {
            "id": uuid.uuid4().hex,
            "asset_id": asset_id,
            "exposure_type": exposure_type,
            "exposure_key": exposure_key,
            "percentage": percentage,
            "source": source,
        },
    )


def _backfill_assets() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            """
            select id, ticker, asset_class, sector, segment, currency, provider_symbol
            from assets
            """
        )
    ).mappings().all()

    for row in rows:
        row_dict = dict(row)
        metadata = _infer_metadata(row_dict)
        connection.execute(
            sa.text(
                """
                update assets
                set
                    universal_symbol = :universal_symbol,
                    asset_subclass = :asset_subclass,
                    country_code = :country_code,
                    region = :region,
                    market = :market,
                    exchange = :exchange,
                    base_currency = :base_currency,
                    trading_currency = :trading_currency,
                    industry = :industry,
                    status = :status
                where id = :id
                """
            ),
            {"id": row_dict["id"], **metadata},
        )

        ticker = _upper(row_dict.get("ticker"))
        provider_symbol = _upper(row_dict.get("provider_symbol"))
        source = "asset_engine_backfill_v1"
        market = metadata["market"]

        _insert_identifier(
            connection,
            asset_id=row_dict["id"],
            identifier_type="universal_symbol",
            identifier_value=metadata["universal_symbol"],
            provider="",
            market=market,
            is_primary=True,
        )
        _insert_identifier(
            connection,
            asset_id=row_dict["id"],
            identifier_type="ticker",
            identifier_value=ticker,
            provider="",
            market=market,
            is_primary=False,
        )
        if provider_symbol and provider_symbol != ticker:
            _insert_identifier(
                connection,
                asset_id=row_dict["id"],
                identifier_type="provider_symbol",
                identifier_value=provider_symbol,
                provider="default",
                market=market,
                is_primary=False,
            )

        _insert_classification(
            connection,
            asset_id=row_dict["id"],
            taxonomy="asset_engine_v1",
            level="asset_class",
            code=_code(row_dict.get("asset_class")),
            label=_clean(row_dict.get("asset_class")),
            source=source,
        )
        _insert_classification(
            connection,
            asset_id=row_dict["id"],
            taxonomy="asset_engine_v1",
            level="asset_subclass",
            code=_code(metadata["asset_subclass"]),
            label=metadata["asset_subclass"],
            source=source,
        )
        _insert_classification(
            connection,
            asset_id=row_dict["id"],
            taxonomy="asset_engine_v1",
            level="sector",
            code=_code(row_dict.get("sector")),
            label=_clean(row_dict.get("sector")),
            source=source,
        )

        if ticker == "IVVB11":
            _insert_exposure(connection, asset_id=row_dict["id"], exposure_type="country", exposure_key="US", percentage=100, source=source)
            _insert_exposure(connection, asset_id=row_dict["id"], exposure_type="region", exposure_key="North America", percentage=100, source=source)
            _insert_exposure(connection, asset_id=row_dict["id"], exposure_type="currency", exposure_key="USD", percentage=100, source=source)
        elif metadata["market"] == "Crypto":
            _insert_exposure(connection, asset_id=row_dict["id"], exposure_type="asset_class", exposure_key="Crypto", percentage=100, source=source)
            _insert_exposure(connection, asset_id=row_dict["id"], exposure_type="currency", exposure_key=metadata["base_currency"], percentage=100, source=source)
        else:
            _insert_exposure(connection, asset_id=row_dict["id"], exposure_type="country", exposure_key=metadata["country_code"], percentage=100, source=source)
            _insert_exposure(connection, asset_id=row_dict["id"], exposure_type="region", exposure_key=metadata["region"], percentage=100, source=source)
            _insert_exposure(connection, asset_id=row_dict["id"], exposure_type="currency", exposure_key=metadata["base_currency"], percentage=100, source=source)


def upgrade() -> None:
    op.add_column("assets", sa.Column("universal_symbol", sa.String(length=96), nullable=True))
    op.add_column("assets", sa.Column("asset_subclass", sa.String(length=80), server_default="", nullable=False))
    op.add_column("assets", sa.Column("country_code", sa.String(length=2), server_default="", nullable=False))
    op.add_column("assets", sa.Column("region", sa.String(length=80), server_default="", nullable=False))
    op.add_column("assets", sa.Column("market", sa.String(length=80), server_default="", nullable=False))
    op.add_column("assets", sa.Column("exchange", sa.String(length=80), server_default="", nullable=False))
    op.add_column("assets", sa.Column("base_currency", sa.String(length=8), server_default="", nullable=False))
    op.add_column("assets", sa.Column("trading_currency", sa.String(length=8), server_default="", nullable=False))
    op.add_column("assets", sa.Column("industry", sa.String(length=120), server_default="", nullable=False))
    op.add_column("assets", sa.Column("isin", sa.String(length=24), server_default="", nullable=False))
    op.add_column("assets", sa.Column("cusip", sa.String(length=24), server_default="", nullable=False))
    op.add_column("assets", sa.Column("status", sa.String(length=32), server_default="active", nullable=False))

    op.create_table(
        "asset_identifiers",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=False),
        sa.Column("identifier_type", sa.String(length=40), nullable=False),
        sa.Column("identifier_value", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("market", sa.String(length=80), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identifier_type", "identifier_value", "provider", "market", name="uq_asset_identifier_scope"),
    )
    op.create_index(op.f("ix_asset_identifiers_asset_id"), "asset_identifiers", ["asset_id"], unique=False)
    op.create_index(op.f("ix_asset_identifiers_identifier_type"), "asset_identifiers", ["identifier_type"], unique=False)
    op.create_index(op.f("ix_asset_identifiers_identifier_value"), "asset_identifiers", ["identifier_value"], unique=False)

    op.create_table(
        "asset_classifications",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=False),
        sa.Column("taxonomy", sa.String(length=80), nullable=False),
        sa.Column("level", sa.String(length=40), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("weight", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "taxonomy", "level", "code", name="uq_asset_classification_scope"),
    )
    op.create_index(op.f("ix_asset_classifications_asset_id"), "asset_classifications", ["asset_id"], unique=False)
    op.create_index(op.f("ix_asset_classifications_level"), "asset_classifications", ["level"], unique=False)
    op.create_index(op.f("ix_asset_classifications_taxonomy"), "asset_classifications", ["taxonomy"], unique=False)

    op.create_table(
        "asset_exposures",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=False),
        sa.Column("exposure_type", sa.String(length=40), nullable=False),
        sa.Column("exposure_key", sa.String(length=120), nullable=False),
        sa.Column("percentage", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_asset_exposures_asset_id"), "asset_exposures", ["asset_id"], unique=False)
    op.create_index(op.f("ix_asset_exposures_exposure_key"), "asset_exposures", ["exposure_key"], unique=False)
    op.create_index(op.f("ix_asset_exposures_exposure_type"), "asset_exposures", ["exposure_type"], unique=False)

    _backfill_assets()
    op.create_index(op.f("ix_assets_universal_symbol"), "assets", ["universal_symbol"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_assets_universal_symbol"), table_name="assets")

    op.drop_index(op.f("ix_asset_exposures_exposure_type"), table_name="asset_exposures")
    op.drop_index(op.f("ix_asset_exposures_exposure_key"), table_name="asset_exposures")
    op.drop_index(op.f("ix_asset_exposures_asset_id"), table_name="asset_exposures")
    op.drop_table("asset_exposures")

    op.drop_index(op.f("ix_asset_classifications_taxonomy"), table_name="asset_classifications")
    op.drop_index(op.f("ix_asset_classifications_level"), table_name="asset_classifications")
    op.drop_index(op.f("ix_asset_classifications_asset_id"), table_name="asset_classifications")
    op.drop_table("asset_classifications")

    op.drop_index(op.f("ix_asset_identifiers_identifier_value"), table_name="asset_identifiers")
    op.drop_index(op.f("ix_asset_identifiers_identifier_type"), table_name="asset_identifiers")
    op.drop_index(op.f("ix_asset_identifiers_asset_id"), table_name="asset_identifiers")
    op.drop_table("asset_identifiers")

    with op.batch_alter_table("assets") as batch_op:
        batch_op.drop_column("status")
        batch_op.drop_column("cusip")
        batch_op.drop_column("isin")
        batch_op.drop_column("industry")
        batch_op.drop_column("trading_currency")
        batch_op.drop_column("base_currency")
        batch_op.drop_column("exchange")
        batch_op.drop_column("market")
        batch_op.drop_column("region")
        batch_op.drop_column("country_code")
        batch_op.drop_column("asset_subclass")
        batch_op.drop_column("universal_symbol")
