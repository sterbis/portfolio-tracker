from datetime import datetime
from typing import Any, NotRequired, TypedDict

from .models import (
    AssetClass,
    Bond,
    Cfd,
    Commodity,
    Crypto,
    DerivativeInstrument,
    Etf,
    Future,
    Instrument,
    InstrumentType,
    Option,
    Stock,
)


INSTRUMENT_CLS_BY_TYPE: dict[InstrumentType, type[Instrument]] = {
    InstrumentType.BOND: Bond,
    InstrumentType.COMMODITY: Commodity,
    InstrumentType.CRYPTO: Crypto,
    InstrumentType.ETF: Etf,
    InstrumentType.STOCK: Stock,
}

DERIVATIVE_INSTRUMENT_CLS_BY_TYPE: dict[InstrumentType, type[DerivativeInstrument]] = {
    InstrumentType.CFD: Cfd,
    InstrumentType.FUTURE: Future,
    InstrumentType.OPTION: Option,
}


class InstrumentBaseData(TypedDict):
    id: NotRequired[str]
    provided_checksum: NotRequired[str]
    name: str
    symbol: str
    exchange: str | None
    currency: str
    last_synced_at: NotRequired[datetime | None]


class DerivativeInstrumentBaseData(TypedDict):
    underlying_instrument_id: str
    asset_class: AssetClass


def create_instrument(
    type_: InstrumentType,
    base_data: InstrumentBaseData,
    details: dict[str, Any],
    derivative_base_data: DerivativeInstrumentBaseData | None = None,
) -> Instrument:
    if type_.is_derivative:
        if derivative_base_data is None:
            raise ValueError(
                f"No derivative instrument base data provided for instrument type {type_}."
            )

        derivative_instrument_cls = DERIVATIVE_INSTRUMENT_CLS_BY_TYPE[type_]
        return derivative_instrument_cls(
            **base_data,
            **derivative_base_data,
            **details,
        )

    instrument_cls = INSTRUMENT_CLS_BY_TYPE[type_]
    return instrument_cls(
        **base_data,
        **details,
    )
