import sqlite3
from collections import defaultdict
from datetime import datetime
from typing import Any, Literal

from filterutils import Filter, FilterNode, Operator

from portfolio_tracker.application.persistence import InstrumentRepository
from portfolio_tracker.domain.instrument import (
    AssetClass,
    Bond,
    Cfd,
    Commodity,
    CouponFrequency,
    Crypto,
    Etf,
    Future,
    Instrument,
    InstrumentBaseData,
    InstrumentMetadata,
    InstrumentType,
    Option,
    OptionType,
    Stock,
    create_instrument,
)

from ..executor import SqliteExecutor


class SqliteInstrumentRepository(InstrumentRepository):
    _table_by_type = {
        InstrumentType.BOND: "bond",
        InstrumentType.CFD: "cfd",
        InstrumentType.COMMODITY: "commodity",
        InstrumentType.CRYPTO: "crypto",
        InstrumentType.ETF: "etf",
        InstrumentType.FUTURE: "future",
        InstrumentType.OPTION: "option",
        InstrumentType.STOCK: "stock",
    }

    def __init__(self, executor: SqliteExecutor) -> None:
        self._executor = executor

    def ensure(self, instrument: Instrument) -> None:
        inserted = self._executor.insert_if_not_exists(
            table="instrument",
            values={
                "instrument_id": instrument.id,
                "checksum": instrument.checksum,
                "type": instrument.type,
                "asset_class": instrument.asset_class,
                "name": instrument.name,
                "symbol": instrument.symbol,
                "exchange": instrument.exchange,
                "currency": instrument.currency,
                "last_synced_at": instrument.last_synced_at,
            },
            conflict_columns=["checksum"],
        )

        if not inserted:
            return

        details = self._get_instrument_details(instrument)
        details["instrument_id"] = instrument.id

        self._executor.insert(
            table=self._table_by_type[instrument.type],
            values=details,
        )

    def get_metadata(
        self,
        *,
        filter_: Filter | None = None,
        order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[InstrumentMetadata]:
        rows = self._executor.select(
            table="instrument",
            filter_=filter_,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        return [self._row_to_metadata(row) for row in rows]

    def get(
        self,
        *,
        filter_: Filter | None = None,
        order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Instrument]:
        metadata_list = self.get_metadata(
            filter_=filter_,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )

        ids_by_instrument_type: dict[InstrumentType, list[str]] = defaultdict(list)

        for metadata in metadata_list:
            ids_by_instrument_type[metadata.type].append(metadata.id)

        details_by_id: dict[str, dict[str, Any]] = {}

        for instrument_type, instrument_ids in ids_by_instrument_type.items():
            rows = self._executor.select(
                table=self._table_by_type[instrument_type],
                filter_=FilterNode("instrument_id", Operator.IN, instrument_ids),
            )
            for row in rows:
                details = self._row_to_instrument_details(instrument_type, row)
                details_by_id[row["instrument_id"]] = details

        instruments: list[Instrument] = []

        for metadata in metadata_list:
            base_data = InstrumentBaseData(
                name=metadata.name,
                symbol=metadata.symbol,
                exchange=metadata.exchange,
                currency=metadata.currency,
                last_synced_at=metadata.last_synced_at,
                _id=metadata.id,
                _checksum=metadata.checksum,
            )
            details = details_by_id[metadata.id]
            instrument = create_instrument(metadata.type, base_data, details)
            instruments.append(instrument)

        return instruments

    def get_by_ids(self, instrument_ids: set[str]) -> list[Instrument]:
        if not instrument_ids:
            return []

        return self.get(
            filter_=FilterNode("instrument_id", Operator.IN, instrument_ids)
        )

    def update_last_synced_at(self, last_synced_at: datetime, instrument_ids: set[str]) -> None:
        self._executor.update(
            table="instrument",
            values={"last_synced_at": last_synced_at},
            filter_=FilterNode("instrument_id", Operator.IN, instrument_ids),
        )

    def _get_instrument_details(self, instrument: Instrument) -> dict[str, Any]:
        match instrument:
            case Bond() as bond:
                details = self._get_bond_details(bond)

            case Cfd() as cfd:
                details = self._get_cfd_details(cfd)

            case Commodity() as commodity:
                details = self._get_commodity_details(commodity)

            case Crypto() as crypto:
                details = self._get_crypto_details(crypto)

            case Etf() as etf:
                details = self._get_etf_details(etf)

            case Future() as future:
                details = self._get_future_details(future)

            case Option() as option:
                details = self._get_option_details(option)

            case Stock() as stock:
                details = self._get_stock_details(stock)

            case _:
                raise ValueError(f"Unsupported instrument type: {type(instrument)}.")

        return details

    def _get_bond_details(self, bond: Bond) -> dict[str, Any]:
        return {
            "isin": bond.isin,
            "face_value": bond.face_value,
            "coupon_rate": bond.coupon_rate,
            "coupon_frequency": bond.coupon_frequency,
            "maturity_on": bond.maturity_on,
        }

    def _get_cfd_details(self, cfd: Cfd) -> dict[str, Any]:
        return {
            "underlying_instrument_id": cfd.underlying_instrument_id,
            "institution_id": cfd.institution_id,
            "leverage": cfd.leverage,
        }

    def _get_commodity_details(self, commodity: Commodity) -> dict[str, Any]:
        return {
            "unit": commodity.unit,
        }

    def _get_crypto_details(self, _: Crypto) -> dict[str, Any]:
        return {}

    def _get_etf_details(self, etf: Etf) -> dict[str, Any]:
        return {
            "isin": etf.isin,
        }

    def _get_future_details(self, future: Future) -> dict[str, Any]:
        return {
            "underlying_instrument_id": future.underlying_instrument_id,
            "isin": future.isin,
            "expiration_on": future.expiration_on,
            "multiplier": future.multiplier,
        }

    def _get_option_details(self, option: Option) -> dict[str, Any]:
        return {
            "underlying_instrument_id": option.underlying_instrument_id,
            "isin": option.isin,
            "expiration_on": option.expiration_on,
            "option_type": option.option_type,
            "strike_price": option.strike_price,
            "multiplier": option.multiplier,
        }

    def _get_stock_details(self, stock: Stock) -> dict[str, Any]:
        return {
            "isin": stock.isin,
        }

    def _row_to_metadata(self, row: sqlite3.Row) -> InstrumentMetadata:
        return InstrumentMetadata(
            id=row["instrument_id"],
            checksum=row["checksum"],
            type=row["type"],
            asset_class=row["asset_class"],
            name=row["name"],
            symbol=row["symbol"],
            exchange=row["exchange"],
            currency=row["currency"],
            last_synced_at=row["last_synced_at"],
            
        )

    def _row_to_instrument_details(
        self, instrument_type: InstrumentType, row: sqlite3.Row
    ) -> dict[str, Any]:
        match instrument_type:
            case InstrumentType.BOND:
                details = self._row_to_bond_details(row)

            case InstrumentType.CFD:
                details = self._row_to_cfd_details(row)

            case InstrumentType.COMMODITY:
                details = self._row_to_commodity_details(row)

            case InstrumentType.CRYPTO:
                details = self._row_to_crypto_details(row)

            case InstrumentType.ETF:
                details = self._row_to_etf_details(row)

            case InstrumentType.FUTURE:
                details = self._row_to_future_details(row)

            case InstrumentType.OPTION:
                details = self._row_to_option_details(row)

            case InstrumentType.STOCK:
                details = self._row_to_stock_details(row)

            case _:
                raise ValueError(f"Unsupported instrument type: {instrument_type}.")

        if instrument_type.is_derivative:
            details["underlying_instrument_id"] = row["underlying_instrument_id"]
            details["_asset_class"] = AssetClass(row["asset_class"])

        return details

    def _row_to_bond_details(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "isin": row["isin"],
            "face_value": row["face_value"],
            "coupon_rate": row["coupon_rate"],
            "coupon_frequency": CouponFrequency(row["coupon_frequency"]),
            "maturity_on": row["maturity_on"],
        }

    def _row_to_cfd_details(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "institution_id": row["institution_id"],
            "leverage": row["leverage"],
        }

    def _row_to_commodity_details(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "unit": row["unit"],
        }

    def _row_to_crypto_details(self, _: sqlite3.Row) -> dict[str, Any]:
        return {}

    def _row_to_etf_details(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "isin": row["isin"],
        }

    def _row_to_future_details(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "isin": row["isin"],
            "expiration_on": row["expiration_on"],
            "multiplier": row["multiplier"],
        }

    def _row_to_option_details(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "isin": row["isin"],
            "expiration_on": row["expiration_on"],
            "option_type": OptionType(row["option_type"]),
            "strike_price": row["strike_price"],
            "multiplier": row["multiplier"],
        }

    def _row_to_stock_details(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "isin": row["isin"],
        }
