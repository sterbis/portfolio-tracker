from datetime import datetime
from typing import Any

from filterutils import Filter, FilterNode, Operator

from portfolio_tracker.application.persistence import InstrumentRepository
from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.domain.instrument import (
    AssetClass,
    Bond,
    Cfd,
    Commodity,
    CouponFrequency,
    Crypto,
    DerivativeInstrumentBaseData,
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
from portfolio_tracker.infrastructure.persistence.sqlite.executor import (
    Row,
    SqliteExecutor,
)
from portfolio_tracker.infrastructure.persistence.sqlite.registry import FieldReference


class SqliteInstrumentRepository(InstrumentRepository):
    _cls_by_type: dict[InstrumentType, type[Instrument]] = {
        InstrumentType.BOND: Bond,
        InstrumentType.CFD: Cfd,
        InstrumentType.COMMODITY: Commodity,
        InstrumentType.CRYPTO: Crypto,
        InstrumentType.ETF: Etf,
        InstrumentType.FUTURE: Future,
        InstrumentType.OPTION: Option,
        InstrumentType.STOCK: Stock,
    }

    def __init__(self, executor: SqliteExecutor) -> None:
        self._executor = executor

    def ensure(self, instrument: Instrument) -> None:
        inserted = self._executor.insert_on_conflict_do_nothing(
            model=Instrument,
            values={
                "id": instrument.id,
                "checksum": instrument.checksum,
                "type": instrument.type,
                "asset_class": instrument.asset_class,
                "name": instrument.name,
                "symbol": instrument.symbol,
                "exchange": instrument.exchange,
                "currency": instrument.currency,
                "last_synced_at": instrument.last_synced_at,
            },
            conflict_field_names=["checksum"],
        )

        if not inserted:
            return

        details = self._get_instrument_details(instrument)
        details["id"] = instrument.id

        self._executor.insert(
            model=type(instrument),
            values=details,
        )

    def get_metadata(
        self,
        *,
        filter_: Filter | None = None,
        sorts: list[Sort] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[InstrumentMetadata]:
        rows = self._executor.select(
            model=InstrumentMetadata,
            filter_=filter_,
            sorts=sorts,
            limit=limit,
            offset=offset,
        )
        return [self._row_to_metadata(row) for row in rows]

    def get(
        self,
        *,
        filter_: Filter | None = None,
        sorts: list[Sort] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Instrument]:
        metadata_list = self.get_metadata(
            filter_=filter_,
            limit=limit,
            offset=offset,
        )

        metadata_by_id: dict[str, InstrumentMetadata] = {}
        instrument_ids_by_type: dict[InstrumentType, list[str]] = {}

        for metadata in metadata_list:
            metadata_by_id[metadata.id] = metadata
            instrument_ids_by_type.setdefault(metadata.type, []).append(metadata.id)

        instruments: list[Instrument] = []

        for instrument_type, instrument_ids in instrument_ids_by_type.items():
            model = self._cls_by_type[instrument_type]

            rows = self._executor.select(
                model=model,
                include_parents=False,
                filter_=FilterNode("id", Operator.IN, instrument_ids, model),
            )

            for row in rows:
                instrument_id = row[FieldReference(model, "id")]
                metadata = metadata_by_id[instrument_id]
                instruments.append(self._row_to_instrument(row, model, metadata))

        if sorts:
            instruments = Sort.apply_many(instruments, sorts)

        return instruments

    def get_by_ids(self, instrument_ids: set[str]) -> list[Instrument]:
        if not instrument_ids:
            return []

        return self.get(
            filter_=FilterNode("id", Operator.IN, instrument_ids, Instrument)
        )

    def get_ids_by_symbols(self, symbols: set[str]) -> set[str]:
        if not symbols:
            return set()

        symbol_field = FieldReference(Instrument, "symbol")

        rows = self._executor.select(
            model=Instrument,
            fields=[symbol_field],
            filter_=FilterNode("symbol", Operator.IN, symbols, Instrument),
        )
        return {row[symbol_field] for row in rows}

    def update_last_synced_at(
        self, instrument_id: str, last_synced_at: datetime
    ) -> None:
        self._executor.update(
            model=Instrument,
            values={"last_synced_at": last_synced_at},
            filter_=FilterNode("id", Operator.EQ, instrument_id, Instrument),
        )

    def _get_instrument_details(self, instrument: Instrument) -> dict[str, Any]:
        match instrument:
            case Bond() as bond:
                return {
                    "isin": bond.isin,
                    "face_value": bond.face_value,
                    "coupon_rate": bond.coupon_rate,
                    "coupon_frequency": bond.coupon_frequency,
                    "maturity_on": bond.maturity_on,
                }

            case Cfd() as cfd:
                return {
                    "underlying_instrument_id": cfd.underlying_instrument_id,
                    "institution_id": cfd.institution_id,
                    "leverage": cfd.leverage,
                }

            case Commodity() as commodity:
                return {
                    "unit": commodity.unit,
                }

            case Crypto():
                return {}

            case Etf() as etf:
                return {
                    "isin": etf.isin,
                }

            case Future() as future:
                return {
                    "underlying_instrument_id": future.underlying_instrument_id,
                    "isin": future.isin,
                    "expiration_on": future.expiration_on,
                    "multiplier": future.multiplier,
                }

            case Option() as option:
                return {
                    "underlying_instrument_id": option.underlying_instrument_id,
                    "isin": option.isin,
                    "expiration_on": option.expiration_on,
                    "option_type": option.option_type,
                    "strike_price": option.strike_price,
                    "multiplier": option.multiplier,
                }

            case Stock() as stock:
                return {
                    "isin": stock.isin,
                }

            case _:
                raise ValueError(f"Unsupported instrument type: {type(instrument)}.")

    def _row_to_metadata(self, row: Row) -> InstrumentMetadata:
        def field(name: str) -> FieldReference:
            return FieldReference(InstrumentMetadata, name)

        return InstrumentMetadata(
            id=row[field("id")],
            checksum=row[field("checksum")],
            type=InstrumentType(row[field("type")]),
            asset_class=AssetClass(row[field("asset_class")]),
            name=row[field("name")],
            symbol=row[field("symbol")],
            exchange=row[field("exchange")],
            currency=row[field("currency")],
            last_synced_at=row[field("last_synced_at")],
        )

    def _row_to_instrument(
        self, row: Row, model: type[Instrument], metadata: InstrumentMetadata
    ) -> Instrument:
        def field(name: str) -> FieldReference:
            return FieldReference(model, name)

        base_data: InstrumentBaseData = {
            "id": metadata.id,
            "provided_checksum": metadata.checksum,
            "name": metadata.name,
            "symbol": metadata.symbol,
            "exchange": metadata.exchange,
            "currency": metadata.currency,
            "last_synced_at": metadata.last_synced_at,
        }

        derivative_base_data: DerivativeInstrumentBaseData | None = None
        if metadata.type.is_derivative:
            derivative_base_data = {
                "underlying_instrument_id": row[field("underlying_instrument_id")],
                "asset_class": AssetClass(row[field("asset_class")]),
            }

        match metadata.type:
            case InstrumentType.BOND:
                details = {
                    "isin": row[field("isin")],
                    "face_value": row[field("face_value")],
                    "coupon_rate": row[field("coupon_rate")],
                    "coupon_frequency": CouponFrequency(row[field("coupon_frequency")]),
                    "maturity_on": row[field("maturity_on")],
                }

            case InstrumentType.CFD:
                details = {
                    "institution_id": row[field("institution_id")],
                    "leverage": row[field("leverage")],
                }

            case InstrumentType.COMMODITY:
                details = {
                    "unit": row[field("unit")],
                }

            case InstrumentType.CRYPTO:
                details = {}

            case InstrumentType.ETF:
                details = {
                    "isin": row[field("isin")],
                }

            case InstrumentType.FUTURE:
                details = {
                    "isin": row[field("isin")],
                    "expiration_on": row[field("expiration_on")],
                    "multiplier": row[field("multiplier")],
                }

            case InstrumentType.OPTION:
                details = {
                    "isin": row[field("isin")],
                    "expiration_on": row[field("expiration_on")],
                    "option_type": OptionType(row[field("option_type")]),
                    "strike_price": row[field("strike_price")],
                    "multiplier": row[field("multiplier")],
                }

            case InstrumentType.STOCK:
                details = {
                    "isin": row[field("isin")],
                }

            case _:
                raise ValueError(f"Unsupported instrument type: {metadata.type}.")

        return create_instrument(
            metadata.type,
            base_data,
            details,
            derivative_base_data,
        )
