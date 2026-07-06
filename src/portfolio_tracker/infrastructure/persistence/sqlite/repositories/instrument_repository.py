import sqlite3
from collections import defaultdict
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
            },
            conflict_columns=["checksum"],
        )

        if not inserted:
            return

        self._executor.insert(
            table=self._table_by_type[instrument.type],
            values=self._instrument_to_values(instrument),
        )

    def get(
        self,
        *,
        filter_: Filter | None = None,
        order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Instrument]:
        rows = self._executor.select(
            table="instrument",
            filter_=filter_,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )

        base_data_by_id: dict[str, InstrumentBaseData] = {}
        ids_by_instrument_type: dict[InstrumentType, list[str]] = defaultdict(list)

        for row in rows:
            instrument_id = row["instrument_id"]
            instrument_type = InstrumentType(row["type"])

            base_data_by_id[instrument_id] = self._row_to_base_data(row)
            ids_by_instrument_type[instrument_type].append(instrument_id)

        details_by_id: dict[str, tuple[InstrumentType, dict[str, Any]]] = {}

        for instrument_type, instrument_ids in ids_by_instrument_type.items():
            rows = self._executor.select(
                table=self._table_by_type[instrument_type],
                filter_=FilterNode("instrument_id", Operator.IN, instrument_ids),
            )
            for row in rows:
                details = self._row_to_instrument_details(instrument_type, row)
                details_by_id[row["instrument_id"]] = (instrument_type, details)

        instruments: list[Instrument] = []

        for instrument_id, base_data in base_data_by_id.items():
            instrument_type, details = details_by_id[instrument_id]

            instrument = create_instrument(instrument_type, base_data, details)
            instruments.append(instrument)

        return instruments

    def get_by_ids(self, instrument_ids: set[str]) -> list[Instrument]:
        if not instrument_ids:
            return []

        return self.get(
            filter_=FilterNode("instrument_id", Operator.IN, instrument_ids)
        )

    def _instrument_to_values(self, instrument: Instrument) -> dict[str, Any]:
        match instrument:
            case Bond() as bond:
                return self._bond_to_values(bond)

            case Cfd() as cfd:
                return self._cfd_to_values(cfd)

            case Commodity() as commodity:
                return self._commodity_to_values(commodity)

            case Crypto() as crypto:
                return self._crypto_to_values(crypto)

            case Etf() as etf:
                return self._etf_to_values(etf)

            case Future() as future:
                return self._future_to_values(future)

            case Option() as option:
                return self._option_to_values(option)

            case Stock() as stock:
                return self._stock_to_values(stock)

            case _:
                raise ValueError(f"Unsupported instrument type: {type(instrument)}.")

    def _bond_to_values(self, bond: Bond) -> dict[str, Any]:
        return {
            "instrument_id": bond.id,
            "isin": bond.isin,
            "face_value": bond.face_value,
            "coupon_rate": bond.coupon_rate,
            "coupon_frequency": bond.coupon_frequency,
            "maturity_on": bond.maturity_on,
        }

    def _cfd_to_values(self, cfd: Cfd) -> dict[str, Any]:
        return {
            "instrument_id": cfd.id,
            "underlying_instrument_id": cfd.underlying_instrument_id,
            "institution_id": cfd.institution_id,
            "leverage": cfd.leverage,
        }

    def _commodity_to_values(self, commodity: Commodity) -> dict[str, Any]:
        return {
            "instrument_id": commodity.id,
            "unit": commodity.unit,
        }

    def _crypto_to_values(self, crypto: Crypto) -> dict[str, Any]:
        return {
            "instrument_id": crypto.id,
        }

    def _etf_to_values(self, etf: Etf) -> dict[str, Any]:
        return {
            "instrument_id": etf.id,
            "isin": etf.isin,
        }

    def _future_to_values(self, future: Future) -> dict[str, Any]:
        return {
            "instrument_id": future.id,
            "underlying_instrument_id": future.underlying_instrument_id,
            "isin": future.isin,
            "expiration_on": future.expiration_on,
            "multiplier": future.multiplier,
        }

    def _option_to_values(self, option: Option) -> dict[str, Any]:
        return {
            "instrument_id": option.id,
            "underlying_instrument_id": option.underlying_instrument_id,
            "isin": option.isin,
            "expiration_on": option.expiration_on,
            "option_type": option.option_type,
            "strike_price": option.strike_price,
            "multiplier": option.multiplier,
        }

    def _stock_to_values(self, stock: Stock) -> dict[str, Any]:
        return {
            "instrument_id": stock.id,
            "isin": stock.isin,
        }

    def _row_to_base_data(self, row: sqlite3.Row) -> InstrumentBaseData:
        return InstrumentBaseData(
            name=row["name"],
            symbol=row["symbol"],
            exchange=row["exchange"],
            currency=row["currency"],
            _id=row["instrument_id"],
            _checksum=row["checksum"],
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
